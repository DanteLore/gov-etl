resource "aws_glue_catalog_table" "world_bank_gdp" {
  name          = "world_bank_gdp"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"        = "parquet"
    "parquet.compression"   = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/world_bank_gdp/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "country_code"
      type = "string"
    }
    columns {
      name = "country_name"
      type = "string"
    }
    columns {
      name = "indicator_id"
      type = "string"
    }
    columns {
      name = "indicator_name"
      type = "string"
    }
    columns {
      name = "year"
      type = "int"
    }
    columns {
      name = "value"
      type = "double"
    }
  }
}
