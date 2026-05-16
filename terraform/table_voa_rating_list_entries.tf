resource "aws_glue_catalog_table" "voa_rating_list_entries" {
  name          = "voa_rating_list_entries"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/voa_rating_list/entries/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "ba_code"
      type = "string"
    }
    columns {
      name = "ndr_community_code"
      type = "string"
    }
    columns {
      name = "uarn"
      type = "string"
    }
    columns {
      name = "desc_code"
      type = "string"
    }
    columns {
      name = "desc_text"
      type = "string"
    }
    columns {
      name = "assessment_reference"
      type = "bigint"
    }
    columns {
      name = "full_address"
      type = "string"
    }
    columns {
      name = "number_or_name"
      type = "string"
    }
    columns {
      name = "street"
      type = "string"
    }
    columns {
      name = "town"
      type = "string"
    }
    columns {
      name = "postal_district"
      type = "string"
    }
    columns {
      name = "county"
      type = "string"
    }
    columns {
      name = "postcode"
      type = "string"
    }
    columns {
      name = "effective_date"
      type = "string"
    }
    columns {
      name = "rateable_value"
      type = "int"
    }
    columns {
      name = "appeal_settlement_code"
      type = "string"
    }
    columns {
      name = "ba_reference"
      type = "string"
    }
    columns {
      name = "list_alteration_date"
      type = "string"
    }
    columns {
      name = "scat_code"
      type = "string"
    }
    columns {
      name = "sub_street_1"
      type = "string"
    }
    columns {
      name = "sub_street_2"
      type = "string"
    }
    columns {
      name = "sub_street_3"
      type = "string"
    }
    columns {
      name = "case_number"
      type = "bigint"
    }
    columns {
      name = "current_from_date"
      type = "string"
    }
  }

  partition_keys {
    name = "postcode_area"
    type = "string"
  }
}
