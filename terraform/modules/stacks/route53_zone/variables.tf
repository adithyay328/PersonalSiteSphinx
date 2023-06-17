# The variables taken in include the
# name of the hosted zone, and some
# basic records to create; this can be
# used for things like google domain
# verification
variable "domain_name" {
    type = string
}

variable "hosted_zone_records" {
    type = list(object({
        name = string
        type = string
        records = list(string)
        ttl = number
    }))
}