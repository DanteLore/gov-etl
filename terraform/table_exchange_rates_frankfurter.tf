resource "aws_glue_catalog_table" "exchange_rates_frankfurter" {
  name          = "exchange_rates_frankfurter"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"        = "parquet"
    "parquet.compression"   = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/exchange_rates/frankfurter/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "date"
      type = "string"
    }
    columns {
      name = "base_currency"
      type = "string"
    }
    columns {
      name = "currency"
      type = "string"
    }
    columns {
      name = "rate"
      type = "double"
    }
  }

  partition_keys {
    name = "year"
    type = "string"
  }
}
