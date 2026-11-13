resource "aws_glue_catalog_table" "osm_cycle_routes" {
  name          = "osm_cycle_routes"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "Cycle routes from the North East Thatcham (SP14) site to Thatcham station, Kennet School and the town centre on OpenStreetMap: length, climb, provision, crossings and gaps"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/osm_cycle_routes/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "origin_id"
      type = "bigint"
    }
    columns {
      name = "origin_lon"
      type = "double"
    }
    columns {
      name = "origin_lat"
      type = "double"
    }
    columns {
      name = "snap_m"
      type = "double"
    }
    columns {
      name = "destination"
      type = "string"
    }
    columns {
      name = "route_type"
      type = "string"
    }
    columns {
      name = "found"
      type = "boolean"
    }
    columns {
      name = "length_m"
      type = "double"
    }
    columns {
      name = "climb_m"
      type = "double"
    }
    columns {
      name = "descent_m"
      type = "double"
    }
    columns {
      name = "max_uphill_pct"
      type = "double"
    }
    columns {
      name = "low_stress_pct"
      type = "double"
    }
    columns {
      name = "cycleway_m"
      type = "double"
    }
    columns {
      name = "cycle_track_m"
      type = "double"
    }
    columns {
      name = "shared_path_m"
      type = "double"
    }
    columns {
      name = "quiet_road_m"
      type = "double"
    }
    columns {
      name = "track_m"
      type = "double"
    }
    columns {
      name = "path_unclear_m"
      type = "double"
    }
    columns {
      name = "cycle_lane_m"
      type = "double"
    }
    columns {
      name = "main_road_m"
      type = "double"
    }
    columns {
      name = "main_roads_crossed"
      type = "bigint"
    }
    columns {
      name = "unmarked_crossings"
      type = "bigint"
    }
    columns {
      name = "unmarked_crossing_roads"
      type = "string"
    }
    columns {
      name = "longest_gap_m"
      type = "double"
    }
    columns {
      name = "longest_gap_ways"
      type = "string"
    }
    columns {
      name = "geometry_wkt"
      type = "string"
    }
  }
}
