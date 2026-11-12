resource "aws_glue_catalog_table" "webtris_counts" {
  name          = "webtris_counts"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "National Highways WebTRIS: 15-minute vehicle counts by length and speed band at the M4 (J12-J14) and A34 count sites near Newbury and Thatcham, about 2017 onwards"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/webtris/counts/"
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
      name = "site_name"
      type = "string"
    }
    columns {
      name = "report_date"
      type = "date"
    }
    columns {
      name = "time_period_ending"
      type = "string"
    }
    columns {
      name = "time_interval"
      type = "int"
    }
    columns {
      name = "vehicles_0_520cm"
      type = "int"
    }
    columns {
      name = "vehicles_521_660cm"
      type = "int"
    }
    columns {
      name = "vehicles_661_1160cm"
      type = "int"
    }
    columns {
      name = "vehicles_over_1160cm"
      type = "int"
    }
    columns {
      name = "vehicles_0_10mph"
      type = "int"
    }
    columns {
      name = "vehicles_11_15mph"
      type = "int"
    }
    columns {
      name = "vehicles_16_20mph"
      type = "int"
    }
    columns {
      name = "vehicles_21_25mph"
      type = "int"
    }
    columns {
      name = "vehicles_26_30mph"
      type = "int"
    }
    columns {
      name = "vehicles_31_35mph"
      type = "int"
    }
    columns {
      name = "vehicles_36_40mph"
      type = "int"
    }
    columns {
      name = "vehicles_41_45mph"
      type = "int"
    }
    columns {
      name = "vehicles_46_50mph"
      type = "int"
    }
    columns {
      name = "vehicles_51_55mph"
      type = "int"
    }
    columns {
      name = "vehicles_56_60mph"
      type = "int"
    }
    columns {
      name = "vehicles_61_70mph"
      type = "int"
    }
    columns {
      name = "vehicles_71_80mph"
      type = "int"
    }
    columns {
      name = "vehicles_over_80mph"
      type = "int"
    }
    columns {
      name = "avg_mph"
      type = "int"
    }
    columns {
      name = "total_volume"
      type = "int"
    }
  }

  partition_keys {
    name = "year"
    type = "string"
  }
}
