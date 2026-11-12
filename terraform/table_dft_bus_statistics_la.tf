resource "aws_glue_catalog_table" "dft_bus_statistics_la" {
  name          = "dft_bus_statistics_la"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "DfT local bus statistics by local authority, England: passenger journeys (BUS01e-h), vehicle miles (BUS02d) and punctuality (BUS09a-b), annual, long format"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/dft_bus_statistics_la/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "table_title"
      type = "string"
    }
    columns {
      name = "unit"
      type = "string"
    }
    columns {
      name = "area_code"
      type = "string"
    }
    columns {
      name = "area_name"
      type = "string"
    }
    columns {
      name = "region"
      type = "string"
    }
    columns {
      name = "service_type"
      type = "string"
    }
    columns {
      name = "year_ending_march"
      type = "bigint"
    }
    columns {
      name = "year_label"
      type = "string"
    }
    columns {
      name = "value"
      type = "double"
    }
    columns {
      name = "value_marker"
      type = "string"
    }
    columns {
      name = "notes"
      type = "string"
    }
    columns {
      name = "edition_published"
      type = "string"
    }
  }

  partition_keys {
    name = "table_id"
    type = "string"
  }
}
