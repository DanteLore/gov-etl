resource "aws_glue_catalog_table" "street_manager_permit_events" {
  name          = "street_manager_permit_events"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "DfT Street Manager open data: roadworks permit and works events in West Berkshire (highway authority SWA 340), 2021 onwards"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/street_manager/permit_events/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "event_reference"
      type = "bigint"
    }
    columns {
      name = "event_type"
      type = "string"
    }
    columns {
      name = "event_time"
      type = "timestamp"
    }
    columns {
      name = "object_type"
      type = "string"
    }
    columns {
      name = "object_reference"
      type = "string"
    }
    columns {
      name = "version"
      type = "int"
    }
    columns {
      name = "work_reference_number"
      type = "string"
    }
    columns {
      name = "permit_reference_number"
      type = "string"
    }
    columns {
      name = "promoter_swa_code"
      type = "string"
    }
    columns {
      name = "promoter_organisation"
      type = "string"
    }
    columns {
      name = "highway_authority"
      type = "string"
    }
    columns {
      name = "highway_authority_swa_code"
      type = "string"
    }
    columns {
      name = "works_location_coordinates"
      type = "string"
    }
    columns {
      name = "street_name"
      type = "string"
    }
    columns {
      name = "area_name"
      type = "string"
    }
    columns {
      name = "town"
      type = "string"
    }
    columns {
      name = "usrn"
      type = "string"
    }
    columns {
      name = "road_category"
      type = "string"
    }
    columns {
      name = "is_traffic_sensitive"
      type = "string"
    }
    columns {
      name = "work_category"
      type = "string"
    }
    columns {
      name = "activity_type"
      type = "string"
    }
    columns {
      name = "traffic_management_type"
      type = "string"
    }
    columns {
      name = "works_location_type"
      type = "string"
    }
    columns {
      name = "is_ttro_required"
      type = "string"
    }
    columns {
      name = "work_status"
      type = "string"
    }
    columns {
      name = "permit_status"
      type = "string"
    }
    columns {
      name = "proposed_start_date"
      type = "string"
    }
    columns {
      name = "proposed_start_time"
      type = "string"
    }
    columns {
      name = "proposed_end_date"
      type = "string"
    }
    columns {
      name = "proposed_end_time"
      type = "string"
    }
    columns {
      name = "actual_start_date_time"
      type = "string"
    }
    columns {
      name = "actual_end_date_time"
      type = "string"
    }
    columns {
      name = "permit_conditions"
      type = "string"
    }
    columns {
      name = "close_footway"
      type = "string"
    }
    columns {
      name = "collaborative_working"
      type = "string"
    }
    columns {
      name = "is_deemed"
      type = "string"
    }
    columns {
      name = "object_data_json"
      type = "string"
    }
  }

  partition_keys {
    name = "event_month"
    type = "string"
  }
}
