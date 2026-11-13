resource "aws_glue_catalog_table" "pct_school_zones" {
  name          = "pct_school_zones"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "Propensity to Cycle Tool: cycling to school now (2011 School Census) and under each scenario, by LSOA of residence, England"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/pct_school_zones/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "geo_code"
      type = "string"
    }
    columns {
      name = "geo_name"
      type = "string"
    }
    columns {
      name = "lad11cd"
      type = "string"
    }
    columns {
      name = "lad_name"
      type = "string"
    }
    columns {
      name = "all"
      type = "double"
    }
    columns {
      name = "bicycle"
      type = "double"
    }
    columns {
      name = "foot"
      type = "double"
    }
    columns {
      name = "car"
      type = "double"
    }
    columns {
      name = "govtarget_slc"
      type = "double"
    }
    columns {
      name = "govtarget_sic"
      type = "double"
    }
    columns {
      name = "govtarget_slw"
      type = "double"
    }
    columns {
      name = "govtarget_siw"
      type = "double"
    }
    columns {
      name = "govtarget_sld"
      type = "double"
    }
    columns {
      name = "govtarget_sid"
      type = "double"
    }
    columns {
      name = "cambridge_slc"
      type = "double"
    }
    columns {
      name = "cambridge_sic"
      type = "double"
    }
    columns {
      name = "cambridge_slw"
      type = "double"
    }
    columns {
      name = "cambridge_siw"
      type = "double"
    }
    columns {
      name = "cambridge_sld"
      type = "double"
    }
    columns {
      name = "cambridge_sid"
      type = "double"
    }
    columns {
      name = "dutch_slc"
      type = "double"
    }
    columns {
      name = "dutch_sic"
      type = "double"
    }
    columns {
      name = "dutch_slw"
      type = "double"
    }
    columns {
      name = "dutch_siw"
      type = "double"
    }
    columns {
      name = "dutch_sld"
      type = "double"
    }
    columns {
      name = "dutch_sid"
      type = "double"
    }
    columns {
      name = "baseline_at_mmet"
      type = "double"
    }
    columns {
      name = "base_slmmet"
      type = "double"
    }
    columns {
      name = "govtarget_simmet"
      type = "double"
    }
    columns {
      name = "cambridge_simmet"
      type = "double"
    }
    columns {
      name = "dutch_simmet"
      type = "double"
    }
    columns {
      name = "base_slcarkm"
      type = "double"
    }
    columns {
      name = "base_slco2"
      type = "double"
    }
    columns {
      name = "govtarget_sicarkm"
      type = "double"
    }
    columns {
      name = "govtarget_sico2"
      type = "double"
    }
    columns {
      name = "dutch_sicarkm"
      type = "double"
    }
    columns {
      name = "cambridge_sico2"
      type = "double"
    }
    columns {
      name = "dutch_sicarkm_1"
      type = "double"
    }
    columns {
      name = "dutch_sico2"
      type = "double"
    }
    columns {
      name = "perc_rf_dist_u5km"
      type = "double"
    }
    columns {
      name = "avslope_perc_u5km"
      type = "double"
    }
  }
}
