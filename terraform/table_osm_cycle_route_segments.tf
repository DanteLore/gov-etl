resource "aws_glue_catalog_table" "osm_cycle_route_segments" {
  name          = "osm_cycle_route_segments"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "The OpenStreetMap ways used by each route in osm_cycle_routes, in order"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/osm_cycle_route_segments/"
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
      name = "seq"
      type = "bigint"
    }
    columns {
      name = "osm_id"
      type = "bigint"
    }
    columns {
      name = "name"
      type = "string"
    }
    columns {
      name = "highway"
      type = "string"
    }
    columns {
      name = "provision"
      type = "string"
    }
    columns {
      name = "maxspeed"
      type = "string"
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
      name = "geometry_wkt"
      type = "string"
    }
  }
}
