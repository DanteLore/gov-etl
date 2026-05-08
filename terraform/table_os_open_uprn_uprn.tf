resource "aws_glue_catalog_table" "os_open_uprn_uprn" {
  name          = "os_open_uprn_uprn"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/os_open_uprn/uprn/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "uprn"
      type = "bigint"
    }
    columns {
      name = "x_coordinate"
      type = "double"
    }
    columns {
      name = "y_coordinate"
      type = "double"
    }
    columns {
      name = "latitude"
      type = "double"
    }
    columns {
      name = "longitude"
      type = "double"
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
