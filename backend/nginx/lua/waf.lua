-- FareFlow WAF - Lua security filter
local _M = {}

-- SQL Injection patterns
local sql_patterns = {
    "union%s+select",
    "insert%s+into",
    "drop%s+table",
    "delete%s+from",
    "exec%s*%(", 
    "xp_cmdshell",
    "information_schema",
    "sleep%s*%(",
    "benchmark%s*%(",
    "load_file%s*%(",
    "into%s+outfile",
    "0x[0-9a-fA-F]+",
}

-- XSS patterns
local xss_patterns = {
    "<script[^>]*>",
    "javascript:",
    "vbscript:",
    "onload%s*=",
    "onerror%s*=",
    "onclick%s*=",
    "onmouseover%s*=",
    "<iframe",
    "<object",
    "expression%s*%(",
    "eval%s*%(",
}

-- Path traversal patterns
local traversal_patterns = {
    "%.%.%/",
    "%.%.\\",
    "%2e%2e%2f",
    "%2e%2e/",
    "..%2f",
}

-- Check string against patterns
local function matches_patterns(str, patterns)
    if not str then return false end
    local lower = string.lower(str)
    for _, pattern in ipairs(patterns) do
        if string.match(lower, pattern) then
            return true, pattern
        end
    end
    return false
end

-- Main WAF check
function _M.check()
    local uri = ngx.var.uri or ""
    local args = ngx.var.args or ""
    local method = ngx.req.get_method()

    -- Check URI
    local blocked, pattern = matches_patterns(uri, sql_patterns)
    if blocked then
        ngx.log(ngx.WARN, "WAF: SQL injection in URI: " .. pattern .. " from " .. ngx.var.remote_addr)
        ngx.exit(444)
        return
    end

    blocked, pattern = matches_patterns(uri, xss_patterns)
    if blocked then
        ngx.log(ngx.WARN, "WAF: XSS in URI: " .. pattern .. " from " .. ngx.var.remote_addr)
        ngx.exit(444)
        return
    end

    blocked, pattern = matches_patterns(uri, traversal_patterns)
    if blocked then
        ngx.log(ngx.WARN, "WAF: Path traversal in URI: " .. pattern .. " from " .. ngx.var.remote_addr)
        ngx.exit(444)
        return
    end

    -- Check query args
    blocked, pattern = matches_patterns(args, sql_patterns)
    if blocked then
        ngx.log(ngx.WARN, "WAF: SQL injection in args: " .. pattern .. " from " .. ngx.var.remote_addr)
        ngx.exit(444)
        return
    end

    blocked, pattern = matches_patterns(args, xss_patterns)
    if blocked then
        ngx.log(ngx.WARN, "WAF: XSS in args: " .. pattern .. " from " .. ngx.var.remote_addr)
        ngx.exit(444)
        return
    end

    -- Check POST body for non-file uploads
    if method == "POST" then
        ngx.req.read_body()
        local body = ngx.req.get_body_data()
        if body and #body < 50000 then  -- Only check bodies under 50KB
            blocked, pattern = matches_patterns(body, sql_patterns)
            if blocked then
                ngx.log(ngx.WARN, "WAF: SQL injection in body: " .. pattern .. " from " .. ngx.var.remote_addr)
                ngx.exit(444)
                return
            end

            blocked, pattern = matches_patterns(body, xss_patterns)
            if blocked then
                ngx.log(ngx.WARN, "WAF: XSS in body: " .. pattern .. " from " .. ngx.var.remote_addr)
                ngx.exit(444)
                return
            end
        end
    end
end

return _M
