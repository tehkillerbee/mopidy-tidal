body = """<!DOCTYPE html>
<html>
<head>
<title>TIDAL OAuth Login</title>
</head>
<body>

<h1>KEEP THIS TAB OPEN</h1>
<a href={authurl} target="_blank" rel="noopener noreferrer">Click here to be forwarded to TIDAL Login page</a>
<p>...then, after login, copy URL of the page you ended up to.</p>
<p>Probably a "not found" page, nevertheless we need the URL</p>
<form method="post">
  <label for="code">Paste here your final URL location:</label>
  <input type="url" id="code" name="code">
  <input type="submit" value="Submit">
</form>

</body>
</html>
""".format