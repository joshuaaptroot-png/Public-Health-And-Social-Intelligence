using CsvHelper;
using System.Globalization;
using System.Reflection;

namespace Public_Health_Local_Ingestion
{
    internal class Program
    {
        static async Task Main(string[] args)
        {
            static async Task DownloadFiles()
            {

                using var reader = new StreamReader("C:\\Users\\Joshu\\OneDrive\\Desktop\\public_health_intelligence\\local ingestion files\\Public-Health-Local-Ingestion\\resource_catalog_rows.csv");
                using var csv = new CsvReader(reader, CultureInfo.InvariantCulture);

                var records = csv.GetRecords<dynamic>().ToList();

                using var http = new HttpClient();

                http.Timeout = Timeout.InfiniteTimeSpan;

                foreach (var record in records)
                {
                    try
                    {
                        Console.WriteLine($"Downloading {record.resource_title}.");


                        string url = record.resource_url;

                        string outputPath = $"C:\\Users\\Joshu\\OneDrive\\Desktop\\NHS_Open_Data\\{record.resource_title}.{record.resource_format}";

                        using var response = await http.GetAsync(
                            url,
                            HttpCompletionOption.ResponseHeadersRead);

                        response.EnsureSuccessStatusCode();

                        var totalBytes = response.Content.Headers.ContentLength;

                        await using var input = await response.Content.ReadAsStreamAsync();
                        await using var output = File.Create(outputPath);

                        var buffer = new byte[81920];
                        long totalRead = 0;
                        int bytesRead;

                        while ((bytesRead = await input.ReadAsync(buffer, 0, buffer.Length)) > 0)
                        {
                            await output.WriteAsync(buffer, 0, bytesRead);

                            totalRead += bytesRead;

                            if (totalBytes.HasValue)
                            {
                                Console.Write($"\r{totalRead * 100.0 / totalBytes.Value:F1}%");
                            }
                        }

                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"Failed to download {record.resource_title}: {ex.Message}");
                    }
                    Console.WriteLine($"Downloaded {record.resource_title}.");
                    
                }
            }

           await DownloadFiles();
        }
    }
}