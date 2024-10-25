import geopandas as gpd
from shapely.geometry import Point

# Replace with the path to your GeoJSON file
input_file = r'C:\Program Files\QGIS 3.34.11\projects\geometri.geojson'
output_file = r'C:\Program Files\QGIS 3.34.11\projects\geometri_errors.geojson'

# Read the GeoJSON file
gdf = gpd.read_file(input_file)

# Reproject the data to EPSG:25832 (ETRS89 / UTM zone 32N) for distance calculations in meters
gdf = gdf.to_crs(epsg=25832)
print(f"Data reprojected to {gdf.crs}")

# Create a set to store indices of geometries involved in topological errors
error_indices = set()

# Separate geometries by type
points = gdf[gdf.geometry.type == 'Point']
lines = gdf[gdf.geometry.type == 'LineString']

print(f"Total point geometries: {len(points)}")
print(f"Total linestring geometries: {len(lines)}")

### Point geometry checks ###

if not points.empty:
    print("Checking point geometries...")
    # Check for duplicate points (same coordinates)
    duplicate_points = points[points.duplicated(subset='geometry', keep=False)]
    
    if not duplicate_points.empty:
        error_indices.update(duplicate_points.index)
        print(f"Found {len(duplicate_points)} duplicate points.")
    else:
        print("No duplicate points found.")
    
    # Check for points within 1 meter of each other
    distance_threshold = 1  # in meters
    
    point_geometries = points.geometry.tolist()
    point_indices = points.index.tolist()
    
    for i in range(len(point_geometries)):
        for j in range(i + 1, len(point_geometries)):
            idx_i = point_indices[i]
            idx_j = point_indices[j]
            point_i = point_geometries[i]
            point_j = point_geometries[j]
            if point_i.distance(point_j) <= distance_threshold:
                error_indices.update([idx_i, idx_j])
                print(f"Point {idx_i} and Point {idx_j}: Points are within {distance_threshold} meters of each other")
else:
    print("No point geometries found.")

### LineString geometry checks ###

if not lines.empty:
    print("Checking linestring geometries...")
    # Identify invalid geometries (e.g., self-intersecting geometries)
    invalid_lines = lines[~lines.is_valid]

    if not invalid_lines.empty:
        error_indices.update(invalid_lines.index)
        print(f"Found {len(invalid_lines)} invalid linestring geometries.")
    else:
        print("No invalid linestring geometries found.")

    # Check for lines that intersect
    line_geometries = lines.geometry.tolist()
    line_indices = lines.index.tolist()
    
    for i in range(len(line_geometries)):
        for j in range(i + 1, len(line_geometries)):
            idx_i = line_indices[i]
            idx_j = line_indices[j]
            geom_i = line_geometries[i]
            geom_j = line_geometries[j]
            if geom_i.intersects(geom_j):
                error_indices.update([idx_i, idx_j])
                print(f"Line {idx_i} and Line {idx_j}: Lines intersect")

    # Check for lines that are too close but do not touch
    distance_threshold = 1  # in meters
    
    for i in range(len(line_geometries)):
        for j in range(i + 1, len(line_geometries)):
            idx_i = line_indices[i]
            idx_j = line_indices[j]
            geom_i = line_geometries[i]
            geom_j = line_geometries[j]
            if geom_i.intersects(geom_j):
                continue  # Skip if they intersect
            if geom_i.distance(geom_j) <= distance_threshold:
                error_indices.update([idx_i, idx_j])
                print(f"Line {idx_i} and Line {idx_j}: Lines are too close but do not touch")

    # Check for lines with endpoints close but not connected
    print("Checking for lines with endpoints close but not connected...")
    # Create a list to hold endpoint data
    endpoints = []
    for idx, line in lines.iterrows():
        start_point = Point(line.geometry.coords[0])
        end_point = Point(line.geometry.coords[-1])
        endpoints.append({'index_line': idx, 'geometry': start_point})
        endpoints.append({'index_line': idx, 'geometry': end_point})

    endpoints_gdf = gpd.GeoDataFrame(endpoints, geometry='geometry', crs=lines.crs)
    endpoint_geometries = endpoints_gdf.geometry.tolist()
    endpoint_indices = endpoints_gdf.index.tolist()
    line_indices_endpoints = endpoints_gdf['index_line'].tolist()

    for i in range(len(endpoint_geometries)):
        for j in range(i + 1, len(endpoint_geometries)):
            idx_i = endpoint_indices[i]
            idx_j = endpoint_indices[j]
            index_line_i = line_indices_endpoints[i]
            index_line_j = line_indices_endpoints[j]
            point_i = endpoint_geometries[i]
            point_j = endpoint_geometries[j]
            if index_line_i == index_line_j:
                continue  # Skip endpoints from the same line
            if point_i.distance(point_j) <= distance_threshold:
                error_indices.update([index_line_i, index_line_j])
                print(f"Line {index_line_i} and Line {index_line_j}: Endpoints are close but not connected")
else:
    print("No linestring geometries found.")

# Combine error indices
print(f"Total geometries with errors: {len(error_indices)}")

# Convert the set to a list before indexing
error_indices_list = list(error_indices)
gdf_errors = gdf.loc[error_indices_list]

# Write the geometries with topological errors to a new GeoJSON file
gdf_errors.to_file(output_file, driver='GeoJSON')

print(f"Geometries with topological errors have been written to {output_file}")
