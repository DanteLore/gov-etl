resource "aws_glue_catalog_table" "webtris_hourly_profiles" {
  name          = "webtris_hourly_profiles"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "National Highways WebTRIS: average vehicles per hour by weekday and month at every WebTRIS site in England, about 2017 onwards"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/webtris/hourly_profiles/"
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
      name = "month_start"
      type = "date"
    }
    columns {
      name = "day_name"
      type = "string"
    }
    columns {
      name = "hour_start"
      type = "int"
    }
    columns {
      name = "average_vehicles"
      type = "int"
    }
    columns {
      name = "days_averaged"
      type = "double"
    }
    columns {
      name = "average_flow_24h"
      type = "int"
    }
    columns {
      name = "large_vehicle_pct_24h"
      type = "double"
    }
  }

  partition_keys {
    name = "year"
    type = "string"
  }
}
