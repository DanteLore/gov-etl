resource "aws_glue_catalog_table" "webtris_daily_flows" {
  name          = "webtris_daily_flows"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "National Highways WebTRIS: daily vehicle flow and large vehicle share at every WebTRIS site in England, about 2017 onwards"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/webtris/daily_flows/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "site_id"
      type = "string"
    }
    columns {
      name = "report_date"
      type = "date"
    }
    columns {
      name = "day_name"
      type = "string"
    }
    columns {
      name = "flow"
      type = "int"
    }
    columns {
      name = "large_vehicle_pct"
      type = "double"
    }
  }

  partition_keys {
    name = "year"
    type = "string"
  }
}
