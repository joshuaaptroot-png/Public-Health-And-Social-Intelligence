import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
Deno.serve(async ()=>{
  const supabase = createClient(Deno.env.get("PROJECT_URL"), Deno.env.get("SERVICE_ROLE_KEY"));
  const { data, error } = await supabase.schema("public").from("package_name_dim").select("*").limit(1);
  return Response.json({
    success: !error,
    data,
    error
  });
});
