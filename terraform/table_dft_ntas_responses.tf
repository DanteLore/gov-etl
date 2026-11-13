resource "aws_glue_catalog_table" "dft_ntas_responses" {
  name          = "dft_ntas_responses"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "DfT National Travel Attitudes Study waves 7-10 (2022-2024): every question, response, percentage and sample size"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/dft_ntas_responses/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "sheet"
      type = "string"
    }
    columns {
      name = "sheet_title"
      type = "string"
    }
    columns {
      name = "question"
      type = "string"
    }
    columns {
      name = "question_base"
      type = "string"
    }
    columns {
      name = "response"
      type = "string"
    }
    columns {
      name = "comparison_variable"
      type = "string"
    }
    columns {
      name = "comparison_value"
      type = "string"
    }
    columns {
      name = "pct"
      type = "double"
    }
    columns {
      name = "value_marker"
      type = "string"
    }
    columns {
      name = "sample_size_response"
      type = "int"
    }
    columns {
      name = "sample_size_base"
      type = "int"
    }
    columns {
      name = "notes"
      type = "string"
    }
    columns {
      name = "variable_name"
      type = "string"
    }
    columns {
      name = "edition_published"
      type = "string"
    }
  }

  partition_keys {
    name = "wave"
    type = "string"
  }
}
