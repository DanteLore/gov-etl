resource "aws_glue_catalog_table" "stats19_casualties" {
  name          = "stats19_casualties"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "DfT road safety data (STATS19): casualties of reported injury road collisions in Great Britain since 1979"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/stats19/stats19_casualties/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "collision_index"
      type = "string"
    }
    columns {
      name = "collision_ref_no"
      type = "string"
    }
    columns {
      name = "vehicle_reference"
      type = "int"
    }
    columns {
      name = "casualty_reference"
      type = "int"
    }
    columns {
      name = "casualty_class"
      type = "int"
    }
    columns {
      name = "sex_of_casualty"
      type = "int"
    }
    columns {
      name = "age_of_casualty"
      type = "int"
    }
    columns {
      name = "age_band_of_casualty"
      type = "int"
    }
    columns {
      name = "casualty_severity"
      type = "int"
    }
    columns {
      name = "pedestrian_location"
      type = "int"
    }
    columns {
      name = "pedestrian_movement"
      type = "int"
    }
    columns {
      name = "car_passenger"
      type = "int"
    }
    columns {
      name = "bus_or_coach_passenger"
      type = "int"
    }
    columns {
      name = "pedestrian_road_maintenance_worker"
      type = "int"
    }
    columns {
      name = "casualty_type"
      type = "int"
    }
    columns {
      name = "casualty_imd_decile"
      type = "int"
    }
    columns {
      name = "lsoa_of_casualty"
      type = "string"
    }
    columns {
      name = "enhanced_casualty_severity"
      type = "int"
    }
    columns {
      name = "casualty_injury_based"
      type = "int"
    }
    columns {
      name = "casualty_adjusted_severity_serious"
      type = "double"
    }
    columns {
      name = "casualty_adjusted_severity_slight"
      type = "double"
    }
    columns {
      name = "casualty_distance_banding"
      type = "int"
    }
    columns {
      name = "escooter_flag"
      type = "int"
    }
  }

  partition_keys {
    name = "collision_year"
    type = "string"
  }
}
