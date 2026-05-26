resource "aws_glue_catalog_table" "nomis_census_industry" {
  name          = "nomis_census_industry"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/nomis_census_industry/industry/"
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
      name = "agriculture_forestry_fishing"
      type = "int"
    }
    columns {
      name = "mining_quarrying"
      type = "int"
    }
    columns {
      name = "manufacturing"
      type = "int"
    }
    columns {
      name = "electricity_gas_steam"
      type = "int"
    }
    columns {
      name = "water_sewerage_waste"
      type = "int"
    }
    columns {
      name = "construction"
      type = "int"
    }
    columns {
      name = "wholesale_retail"
      type = "int"
    }
    columns {
      name = "transport_storage"
      type = "int"
    }
    columns {
      name = "accommodation_food"
      type = "int"
    }
    columns {
      name = "information_communication"
      type = "int"
    }
    columns {
      name = "financial_insurance"
      type = "int"
    }
    columns {
      name = "real_estate"
      type = "int"
    }
    columns {
      name = "professional_scientific"
      type = "int"
    }
    columns {
      name = "administrative_support"
      type = "int"
    }
    columns {
      name = "public_administration_defence"
      type = "int"
    }
    columns {
      name = "education"
      type = "int"
    }
    columns {
      name = "health_social_work"
      type = "int"
    }
    columns {
      name = "other"
      type = "int"
    }
  }
}
