resource "aws_glue_catalog_table" "stats19_vehicles" {
  name          = "stats19_vehicles"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "DfT road safety data (STATS19): vehicles involved in reported injury road collisions in Great Britain since 1979"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/stats19/stats19_vehicles/"
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
      name = "vehicle_type"
      type = "int"
    }
    columns {
      name = "towing_and_articulation"
      type = "int"
    }
    columns {
      name = "vehicle_manoeuvre_historic"
      type = "int"
    }
    columns {
      name = "vehicle_manoeuvre"
      type = "int"
    }
    columns {
      name = "vehicle_direction_from"
      type = "int"
    }
    columns {
      name = "vehicle_direction_to"
      type = "int"
    }
    columns {
      name = "vehicle_location_restricted_lane_historic"
      type = "int"
    }
    columns {
      name = "vehicle_location_restricted_lane"
      type = "int"
    }
    columns {
      name = "junction_location"
      type = "int"
    }
    columns {
      name = "skidding_and_overturning"
      type = "int"
    }
    columns {
      name = "hit_object_in_carriageway"
      type = "int"
    }
    columns {
      name = "vehicle_leaving_carriageway"
      type = "int"
    }
    columns {
      name = "hit_object_off_carriageway"
      type = "int"
    }
    columns {
      name = "first_point_of_impact"
      type = "int"
    }
    columns {
      name = "vehicle_left_hand_drive"
      type = "int"
    }
    columns {
      name = "journey_purpose_of_driver_historic"
      type = "int"
    }
    columns {
      name = "journey_purpose_of_driver"
      type = "int"
    }
    columns {
      name = "sex_of_driver"
      type = "int"
    }
    columns {
      name = "age_of_driver"
      type = "int"
    }
    columns {
      name = "age_band_of_driver"
      type = "int"
    }
    columns {
      name = "engine_capacity_cc"
      type = "int"
    }
    columns {
      name = "propulsion_code"
      type = "int"
    }
    columns {
      name = "age_of_vehicle"
      type = "int"
    }
    columns {
      name = "generic_make_model"
      type = "string"
    }
    columns {
      name = "driver_imd_decile"
      type = "int"
    }
    columns {
      name = "lsoa_of_driver"
      type = "string"
    }
    columns {
      name = "escooter_flag"
      type = "int"
    }
    columns {
      name = "driver_distance_banding"
      type = "int"
    }
  }

  partition_keys {
    name = "collision_year"
    type = "string"
  }
}
