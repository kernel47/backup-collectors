from outputs.http import HttpOutput


class LogstashOutput(HttpOutput):
    destination = "Logstash"
