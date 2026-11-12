using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Validation;

if (args.Length == 0) return 2;
var failed = false;
foreach (var path in args)
{
    using var document = PresentationDocument.Open(path, false, new OpenSettings { MaxCharactersInPart = 0 });
    var validator = new OpenXmlValidator(FileFormatVersions.Office2019) { MaxNumberOfErrors = 100 };
    var errors = validator.Validate(document).ToArray();
    Console.WriteLine($"{Path.GetFileName(path)}: {errors.Length} Open XML errors");
    foreach (var error in errors)
        Console.WriteLine($"{error.Part?.Uri} {error.Path?.XPath}: {error.Description}");
    failed |= errors.Length > 0;
}
return failed ? 1 : 0;
