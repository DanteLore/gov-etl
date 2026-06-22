resource "aws_glue_catalog_table" "ea_lidar_1m_dtm" {
  name          = "ea_lidar_1m_dtm"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/ea_lidar_1m/dtm/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "x_coordinate"
      type = "int"
    }
    columns {
      name = "y_coordinate"
      type = "int"
    }
    columns {
      name = "elevation_m"
      type = "float"
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
