provider "aws" {
  region  = "eu-west-1"
  profile = "dantelore"

  default_tags {
    tags = {
      Project    = "gov-etl"
      Repository = "https://github.com/DanteLore/gov-etl"
      ManagedBy  = "terraform"
    }
  }
}