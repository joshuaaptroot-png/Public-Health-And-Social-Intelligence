Deno.serve(async ()=>{
  const packageName = "foi-02279";
  const response = await fetch(`https://opendata.nhsbsa.net/api/3/action/package_show?id=${packageName}`);
  const payload = await response.json();
  return Response.json(payload);
});
