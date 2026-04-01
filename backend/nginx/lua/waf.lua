-- FareFlow WAF - Lua security filter

local sql_patterns = {
    "union.+select",
    "insert.+into",
    "drop.+table",
    "delete.+from",
    "exec%s*%(",
    "xp_cmdshell",
    "information_schema",
    "sleep%s*%(",
    "benchmark%s*%(",
    "load_file%s*%(",
    "into.+outfile",
    "or%s+1%s*=%s*1",
    "or%s+'1'%s*=%s*'1'",
    "select.+from",
    "waitfor.+delay",
}

local xss_patterns = {
    "<script",
    "javascript:",
    "vbscript:",
    "onload%s*=",
    "onerror%s*=",
    "onclick%s*=",
    "onmouseover%s*=",
    "<iframe",
    "<object",
    "eval%s*%(",
    "document%.cookie",
    "document%.write",
    "window%.location",
}

local traversal_patterns = {
    "%.%.%/",
    "%.%.\\",
    "etc%/passwd",
    "etc%/shadow",
    "proc%/self",
    "win%.ini",
    "boot%.ini",
}

local function decode_uri(str)
    if not str then return "" end
    -- Decode URL encoding
    str = string.gsub(str, "%%(%x%x)", function(h)
        return string.char(tonumber(h, 16))
    end)
    -- Replace + with space
    str = string.gsub(str, "%+", " ")
    return str
end

local function check_patterns(str, patterns)
    if not str then return false, nil end
    local decoded = decode_uri(str)
    local lower = string.lower(decoded)
    for _, pattern in ipairs(patterns) do
        local ok, res = pcall(string.match, lower, pattern)
        if ok and res then
            return true, pattern
        end
    end
    return false, nil
end

local function block(reason, pattern)
    ngx.log(ngx.WARN, "WAF BLOCK [" .. reason .. "] pattern=" .. tostring(pattern) .. " ip=" .. ngx.var.remote_addr .. " uri=" .. ngx.var.uri)
    return ngx.exit(444)
end

local uri = ngx.var.uri or ""
local args = ngx.var.args or ""
local full = uri .. "?" .. args

local blocked, pattern = check_patterns(full, sql_patterns)
if blocked then return block("SQLi", pattern) end

blocked, pattern = check_patterns(full, xss_patterns)
if blocked then return block("XSS", pattern) end

blocked, pattern = check_patterns(full, traversal_patterns)
if blocked then return block("Traversal", pattern) end

if ngx.req.get_method() == "POST" then
    ngx.req.read_body()
    local body = ngx.req.get_body_data()
    if body and #body < 50000 then
        blocked, pattern = check_patterns(body, sql_patterns)
        if blocked then return block("SQLi-body", pattern) end

        blocked, pattern = check_patterns(body, xss_patterns)
        if blocked then return block("XSS-body", pattern) end
    end
end
