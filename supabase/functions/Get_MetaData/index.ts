import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
Deno.serve(async ()=>{
  const supabase = createClient(Deno.env.get("PROJECT_URL"), Deno.env.get("SERVICE_ROLE_KEY"));
  const { data: packages, error: packageError } = await supabase.from("package_name_dim").select("package_name");
  if (packageError) {
    return Response.json({
      error: packageError.message
    }, {
      status: 500
    });
  }
  let resourcesFound = 0;
  let packagesProcessed = 0;
  for (const pkg of packages ?? []){
    const packageName = pkg.package_name;
    const response = await fetch(`https://opendata.nhsbsa.net/api/3/action/package_show?id=${encodeURIComponent(packageName)}`);
    const payload = await response.json();
    if (!payload.success || !payload.result?.resources) {
      console.log(`Skipped package: ${packageName}`);
      continue;
    }
    const rows = payload.result.resources.map((resource)=>({
        package_name: packageName,
        package_title: payload.result.title ?? null,
        resource_id: resource.id,
        resource_name: resource.name ?? null,
        resource_title: resource.title ?? null,
        resource_format: resource.format ?? null,
        resource_url: resource.url ?? null,
        resource_size: resource.size ?? null,
        metadata_modified: resource.metadata_modified ?? null,
        updated_at: new Date().toISOString()
      }));
    if (rows.length > 0) {
      const { error: upsertError } = await supabase.from("resource_catalog").upsert(rows, {
        onConflict: "resource_id"
      });
      if (upsertError) {
        console.error(`Failed package ${packageName}:`, upsertError);
        continue;
      }
      resourcesFound += rows.length;
    }
    packagesProcessed++;
  }
  return Response.json({
    success: true,
    packages_processed: packagesProcessed,
    resources_found: resourcesFound
  });
});
