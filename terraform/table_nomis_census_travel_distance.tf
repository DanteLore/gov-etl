resource "aws_glue_catalog_table" "nomis_census_travel_distance" {
  name          = "nomis_census_travel_distance"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "Census 2021 TS058 distance travelled to work, England and Wales by output area, LSOA, MSOA, local authority and ward"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/nomis_census_travel_distance/"
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
      name = "total"
      type = "int"
    }
    columns {
      name = "under_2km"
      type = "int"
    }
    columns {
      name = "from_2_to_5km"
      type = "int"
    }
    columns {
      name = "from_5_to_10km"
      type = "int"
    }
    columns {
      name = "from_10_to_20km"
      type = "int"
    }
    columns {
      name = "from_20_to_30km"
      type = "int"
    }
    columns {
      name = "from_30_to_40km"
      type = "int"
    }
    columns {
      name = "from_40_to_60km"
      type = "int"
    }
    columns {
      name = "km_60_and_over"
      type = "int"
    }
    columns {
      name = "work_from_home"
      type = "int"
    }
    columns {
      name = "offshore_no_fixed_place_or_abroad"
      type = "int"
    }
  }

  partition_keys {
    name = "geography_level"
    type = "string"
  }
}
