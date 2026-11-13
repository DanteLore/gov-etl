resource "aws_glue_catalog_table" "dft_nts_tables" {
  name          = "dft_nts_tables"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "DfT National Travel Survey published tables (NTS0101-NTS9920 and combined authority estimates), England, long format"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/dft_nts_tables/"
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
      name = "year_label"
      type = "string"
    }
    columns {
      name = "year"
      type = "int"
    }
    columns {
      name = "dimension_1_name"
      type = "string"
    }
    columns {
      name = "dimension_1"
      type = "string"
    }
    columns {
      name = "dimension_2_name"
      type = "string"
    }
    columns {
      name = "dimension_2"
      type = "string"
    }
    columns {
      name = "dimension_3_name"
      type = "string"
    }
    columns {
      name = "dimension_3"
      type = "string"
    }
    columns {
      name = "measure"
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
      name = "sample_size"
      type = "double"
    }
    columns {
      name = "sample_size_label"
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
