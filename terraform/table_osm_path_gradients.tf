resource "aws_glue_catalog_table" "osm_path_gradients" {
  name          = "osm_path_gradients"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "Gradient of every OpenStreetMap road and path where the EA 1m lidar is loaded: heights, climb, descent, steepest 50 m, quality flag and 10 m profile"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/osm_path_gradients/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "osm_id"
      type = "bigint"
    }
    columns {
      name = "highway"
      type = "string"
    }
    columns {
      name = "name"
      type = "string"
    }
    columns {
      name = "length_m"
      type = "double"
    }
    columns {
      name = "elevation_start_m"
      type = "double"
    }
    columns {
      name = "elevation_end_m"
      type = "double"
    }
    columns {
      name = "elevation_min_m"
      type = "double"
    }
    columns {
      name = "elevation_max_m"
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
      name = "max_downhill_pct"
      type = "double"
    }
    columns {
      name = "mean_gradient_pct"
      type = "double"
    }
    columns {
      name = "is_interpolated"
      type = "boolean"
    }
    columns {
      name = "gradient_check"
      type = "string"
    }
    columns {
      name = "elevation_profile_m"
      type = "array<double>"
    }
  }

  partition_keys {
    name = "grid_e"
    type = "int"
  }

  partition_keys {
    name = "grid_n"
    type = "int"
  }
}
