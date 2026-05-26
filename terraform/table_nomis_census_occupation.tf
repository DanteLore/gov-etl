resource "aws_glue_catalog_table" "nomis_census_occupation" {
  name          = "nomis_census_occupation"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/nomis_census_occupation/occupation/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "ward_cd"
      type = "string"
    }
    columns {
      name = "ward_nm"
      type = "string"
    }
    columns {
      name = "total"
      type = "int"
    }
    columns {
      name = "managers_directors_senior_officials"
      type = "int"
    }
    columns {
      name = "professional"
      type = "int"
    }
    columns {
      name = "associate_professional_technical"
      type = "int"
    }
    columns {
      name = "administrative_secretarial"
      type = "int"
    }
    columns {
      name = "skilled_trades"
      type = "int"
    }
    columns {
      name = "caring_leisure_service"
      type = "int"
    }
    columns {
      name = "sales_customer_service"
      type = "int"
    }
    columns {
      name = "process_plant_machine_operatives"
      type = "int"
    }
    columns {
      name = "elementary"
      type = "int"
    }
  }
}
