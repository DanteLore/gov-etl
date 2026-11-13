resource "aws_glue_catalog_table" "pct_route_network" {
  name          = "pct_route_network"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "Propensity to Cycle Tool route network: cyclists per road or path segment now and under each scenario, commute (England and Wales) and school (England)"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/pct_route_network/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "local_id"
      type = "bigint"
    }
    columns {
      name = "bicycle"
      type = "double"
    }
    columns {
      name = "govtarget_slc"
      type = "double"
    }
    columns {
      name = "govnearmkt_slc"
      type = "double"
    }
    columns {
      name = "gendereq_slc"
      type = "double"
    }
    columns {
      name = "dutch_slc"
      type = "double"
    }
    columns {
      name = "ebike_slc"
      type = "double"
    }
    columns {
      name = "cambridge_slc"
      type = "double"
    }
    columns {
      name = "min_lon"
      type = "double"
    }
    columns {
      name = "min_lat"
      type = "double"
    }
    columns {
      name = "max_lon"
      type = "double"
    }
    columns {
      name = "max_lat"
      type = "double"
    }
    columns {
      name = "geometry_wkt"
      type = "string"
    }
  }

  partition_keys {
    name = "purpose"
    type = "string"
  }
}
