const { GoogleAuth } = require('google-auth-library');
const { google } = require('googleapis');

exports.handler = async (event) => {
    const trackingNum = event.queryStringParameters.number;
    
    try {
        const auth = new GoogleAuth({
            credentials: {
                client_email: process.env.GOOGLE_CLIENT_EMAIL,
                private_key: process.env.GOOGLE_PRIVATE_KEY.replace(/\\n/g, '\n')
            },
            scopes: ['https://www.googleapis.com/auth/spreadsheets']
        });

        const sheets = google.sheets({ version: 'v4', auth });
        const response = await sheets.spreadsheets.values.get({
            spreadsheetId: process.env.SHEET_ID,
            range: 'Sheet1!A:C'
        });

        const row = response.data.values.find(r => r[0] === trackingNum);
        return {
            statusCode: 200,
            body: JSON.stringify(row 
                ? { status: row[1], location: row[2] } 
                : { error: 'Not found' }
            )
        };
    } catch (error) {
        console.error("Error:", error);
        return {
            statusCode: 500,
            body: JSON.stringify({ error: 'Server error' })
        };
    }
};