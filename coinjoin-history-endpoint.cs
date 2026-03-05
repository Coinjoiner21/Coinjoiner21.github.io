// Add this endpoint to WabiSabiController.cs after the GetHumanMonitor() method.
// Also add "using System.IO;" to the top of the file.

[HttpGet("coinjoin-history")]
public IActionResult GetCoinJoinHistory()
{
	var dataDir = Path.GetDirectoryName(WalletWasabi.Logging.Logger.FilePath)!;
	var historyFile = Path.Combine(dataDir, "coinjoin-history.json");

	if (!System.IO.File.Exists(historyFile))
	{
		return Content("[]", "application/json");
	}

	using var stream = new FileStream(historyFile, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
	using var reader = new StreamReader(stream);
	return Content(reader.ReadToEnd(), "application/json");
}
