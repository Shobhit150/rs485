import AlisteSDK from "aliste-sdk"

const sdk = new AlisteSDK({
  baseURL: "http://localhost:3000",
  apiKey: "test"
})

async function run() {
  const res = await sdk.logAPI({
    success: "true",
    data: "relay_on"
  })

  console.log(res)
}

run()