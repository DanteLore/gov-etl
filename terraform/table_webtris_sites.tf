resource "aws_glue_catalog_table" "webtris_sites" {
  name          = "webtris_sites"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "National Highways WebTRIS: every traffic count site in England with location and status"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/webtris/sites/"
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
      name = "description"
      type = "string"
    }
    columns {
      name = "longitude"
      type = "double"
    }
    columns {
      name = "latitude"
      type = "double"
    }
    columns {
      name = "status"
      type = "string"
    }
  }

}
