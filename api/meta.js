export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).send('Method Not Allowed');
  }
  
  try {
    const { targetUrl } = req.body;
    
    // The frontend sends a URL with a fake token. 
    // We swap it out for the REAL token stored securely in Vercel's vault.
    const realToken = process.env.META_ACCESS_TOKEN;
    const finalUrl = targetUrl.replace('hidden_in_backend', realToken);
    
    // Fetch from Meta and return to frontend
    const metaResponse = await fetch(finalUrl);
    const data = await metaResponse.json();
    
    res.status(200).json(data);
  } catch (error) {
    res.status(500).json({ error: { message: "Backend proxy error" } });
  }
}
