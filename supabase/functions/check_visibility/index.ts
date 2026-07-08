import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
Deno.serve(async ()=>{
  const supabase = createClient(Deno.env.get("PROJECT_URL"), Deno.env.get("SERVICE_ROLE_KEY"));
  const result = await supabase.from("package_name_dim").select("*").limit(1);
  return Response.json(result);
});
