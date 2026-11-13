resource "aws_glue_catalog_table" "nomis_census_2011_travel_method" {
  name          = "nomis_census_2011_travel_method"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "Census 2011 QS701EW method of travel to work by output area, LSOA, MSOA, 2011 ward and local authority, England and Wales"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/nomis_census_2011_travel_method/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "geography_code"
      type = "string"
    }
    columns {
      name = "geography_name"
      type = "string"
    }
    columns {
      name = "all_methods"
      type = "int"
    }
    columns {
      name = "work_from_home"
      type = "int"
    }
    columns {
      name = "underground_metro_tram"
      type = "int"
    }
    columns {
      name = "train"
      type = "int"
    }
    columns {
      name = "bus_coach"
      type = "int"
    }
    columns {
      name = "taxi"
      type = "int"
    }
    columns {
      name = "motorcycle"
      type = "int"
    }
    columns {
      name = "car_driver"
      type = "int"
    }
    columns {
      name = "car_passenger"
      type = "int"
    }
    columns {
      name = "bicycle"
      type = "int"
    }
    columns {
      name = "on_foot"
      type = "int"
    }
    columns {
      name = "other"
      type = "int"
    }
    columns {
      name = "not_in_employment"
      type = "int"
    }
  }

  partition_keys {
    name = "geography_level"
    type = "string"
  }
}
