include {
  path = find_in_parent_folders("root.hcl")
}

inputs = {
  hosted_zone_records = [
    # {
    #     name = "adithyay.com"
    #     type = "TXT"
    #     ttl = 300
    #     records = ["google-site-verification=h3oYqcX-WPAzZtbzZB0NYJpTB-tAxU8Of-hLr4YMgMY"]
    # },
    # {
    #     name = "_github-pages-challenge-adithyay328.adithyay.com"
    #     type = "TXT"
    #     ttl = 300
    #     records = ["1114a4c1e821b527702e56978f5b7f"]
    # }
  ]
}