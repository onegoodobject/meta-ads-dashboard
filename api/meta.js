export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).send('Method Not Allowed');
  }
  
  try {
    const { targetUrl } = req.body;
    const realToken = process.env.META_ACCESS_TOKEN;
    
    // Check if token exists in Vercel
    if (!realToken) {
      return res.status(200).json({ 
        error: { message: "VERCEL ERROR: META_ACCESS_TOKEN is missing in Vercel settings." } 
      });
    }

    // Bulletproof way to inject the token into the Meta URL
    const urlObj = new URL(targetUrl);
    urlObj.searchParams.set('access_token', realToken.trim());
    const finalUrl = urlObj.toString();
    
    // Fetch from Meta
    const metaResponse = await fetch(finalUrl);
    const data = await metaResponse.json();
    
    // If Meta still throws an error, add a debug tag so we can see if the token is corrupted
    if (data.error) {
      data.error.message = `META REJECTED TOKEN: ${data.error.message} (Token sent started with: ${realToken.substring(0, 6)}...)`;
    }
    
    return res.status(200).json(data);
  } catch (error) {
    return res.status(200).json({ 
      error: { message: "Backend proxy error: " + error.message } 
    });
  }
}
