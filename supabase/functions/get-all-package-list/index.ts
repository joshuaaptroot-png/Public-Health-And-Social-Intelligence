import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
Deno.serve(async ()=>{
  const supabase = createClient(Deno.env.get("PROJECT_URL"), Deno.env.get("SERVICE_ROLE_KEY"));
  // Get package list from NHSBSA
  const response = await fetch("https://opendata.nhsbsa.net/api/3/action/package_list");
  const payload = await response.json();
  if (!payload.success) {
    return Response.json({
      error: "Failed to retrieve NHS package list"
    }, {
      status: 500
    });
  }
  // Convert package names into rows
  const rows = payload.result.map((packageName)=>({
      package_name: packageName
    }));
  // Upsert into dimension table
  const result = await supabase.from("package_name_dim").upsert(rows, {
    onConflict: "package_name"
  });
  return Response.json({
    packages_found: rows.length,
    error: result.error
  });
});
