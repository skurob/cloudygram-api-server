﻿using System;
using System.IO;
using System.Text;
using System.Net.Http;
using System.Threading.Tasks;

namespace test_file
{
    class Program
    {
        static public string BASE_PATH = "./";
        static public string URL = "http://127.0.0.1:5000/user/+393421323295/uploadFile";
        static public string API_FILE_KEY = "file";

        static void Main(string[] args)
        {
            Console.Write("insert file name: ");
            var fileName = Console.ReadLine();
            Console.Write("insert file content(txt): ");
            var fileContent = Console.ReadLine();
            CreateFile(fileContent);
            Console.WriteLine(SendFile(fileName));
        }

        static void CreateFile(string fileName, string fileContent)
        {
            byte[] toWrite = Encoding.ASCII.GetBytes(fileContent);
            var f = new FileStream(BASE_PATH + fileName, FileMode.OpenOrCreate);
            f.Write(toWrite, 0, toWrite.Length);
            f.Close();
        }

        static bool SendFile(string fileName)
        {
            Stream r = new FileStream(PATH, FileMode.Open);
            HttpContent content = new StreamContent(r);
            using (var client = new HttpClient())
            using (var formData = new MultipartFormDataContent())
            {
                formData.Add(content, API_FILE_KEY, fileName);
                var resp = client.PostAsync(URL, formData).Result;
                return resp.IsSuccessStatusCode;
            }
        }
    }
}
