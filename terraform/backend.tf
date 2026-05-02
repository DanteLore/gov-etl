terraform {
  backend "s3" {
    bucket  = "dantelore.tfstate"
    key     = "gov-etl.tfstate"
    region  = "eu-west-1"
    profile = "dantelore"
  }
}
