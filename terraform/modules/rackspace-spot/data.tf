# Find all server classes with less than 8GB of memory and 4 CPUs

data "spot_serverclasses" "all" {
  filters = [
    {
      name   = "resources.memory"
      values = [">8GB"]
    },
    {
      name   = "resources.cpu"
      values = ["4"]
    }
  ]
}