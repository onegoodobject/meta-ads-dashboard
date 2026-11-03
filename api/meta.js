export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).send('Method Not Allowed');
  }
  
  try {
    const { targetUrl } = req.body;
    const realToken = process.env.META_ACCESS_TOKEN;
    
    // Diagnostic Check 1: Did Vercel load the token?
    if (!realToken) {
      return res.status(200).json({ 
        error: { message: "VERCEL ERROR: Your META_ACCESS_TOKEN is missing or empty in Vercel's Environment Variables." } 
      });
    }

    // Diagnostic Check 2: Did the frontend send the URL?
    if (!targetUrl) {
      return res.status(200).json({ 
        error: { message: "VERCEL ERROR: No targetUrl was received from the frontend." } 
      });
    }
    
    const finalUrl = targetUrl.replace('hidden_in_backend', realToken);
    
    const metaResponse = await fetch(finalUrl);
    const data = await metaResponse.json();
    
    return res.status(200).json(data);
  } catch (error) {
    return res.status(200).json({ 
      error: { message: "Backend proxy error: " + error.message } 
    });
  }
}
