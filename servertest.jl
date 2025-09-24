using HTTP, JSON3
BASE = "http://localhost:1234/v1"
headers = ["Content-Type"=>"application/json","Accept"=>"application/json","Authorization"=>"Bearer lm-studio"]
payload = Dict("model"=>"qwen2.5-7b-instruct",
"messages"=>[Dict("role"=>"user","content"=>"Say 'pong'.")])
body = Vector{UInt8}(JSON3.write(payload))
resp = HTTP.request("POST", "$BASE/chat/completions", headers, body; status_exception=false)
println(resp.status, " ", String(resp.body))
