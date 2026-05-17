resource "aws_glue_catalog_table" "ons_inflation_inflation" {
  name          = "ons_inflation_inflation"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/ons_inflation/inflation/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "year"
      type = "int"
    }
    columns {
      name = "month"
      type = "int"
    }
    columns {
      name = "cpi_index"
      type = "double"
    }
    columns {
      name = "cpi_rate"
      type = "double"
    }
    columns {
      name = "cpih_index"
      type = "double"
    }
    columns {
      name = "cpih_rate"
      type = "double"
    }
    columns {
      name = "rpi_rate"
      type = "double"
    }
  }
}
