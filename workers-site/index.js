import { getAssetFromKV, mapRequestToAsset } from '@cloudflare/kv-asset-handler'

/**
 * 处理事件
 * @param {FetchEvent} event
 */
async function handleEvent(event) {
  const url = new URL(event.request.url)
  let options = {}

  try {
    // 获取静态资源
    const page = await getAssetFromKV(event, options)
    
    // 设置缓存控制
    const response = new Response(page.body, page)
    response.headers.set('X-XSS-Protection', '1; mode=block')
    response.headers.set('X-Content-Type-Options', 'nosniff')
    response.headers.set('X-Frame-Options', 'DENY')
    response.headers.set('Referrer-Policy', 'unsafe-url')
    response.headers.set('Feature-Policy', 'none')
    
    return response
  } catch (e) {
    // 如果资源不存在
    if (e.status === 404 || e.status === 410) {
      // 尝试渲染索引页面
      try {
        const notFoundResponse = await getAssetFromKV(event, {
          mapRequestToAsset: req => new Request(`${new URL(req.url).origin}/index.html`, req),
        })

        return new Response(notFoundResponse.body, { ...notFoundResponse, status: 404 })
      } catch (e) {}
    }

    return new Response(e.message || 'Not Found', { status: e.status || 404 })
  }
}

addEventListener('fetch', event => {
  try {
    event.respondWith(handleEvent(event))
  } catch (e) {
    event.respondWith(new Response('Internal Error', { status: 500 }))
  }
}) 