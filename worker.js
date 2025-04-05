addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

/**
 * 处理请求
 * @param {Request} request
 */
async function handleRequest(request) {
  // URL路径
  const url = new URL(request.url)
  const path = url.pathname

  // 处理静态文件
  if (path.startsWith('/static/')) {
    return await handleStatic(request)
  }

  // 路由处理
  if (path === '/' || path === '/index') {
    return await renderPage('index.html')
  } else if (path.startsWith('/game/')) {
    const gameId = path.replace('/game/', '')
    return await renderPage('detail.html', { gameId })
  }

  // 404页面
  return new Response('页面不存在', {
    status: 404,
    headers: { 'Content-Type': 'text/plain;charset=UTF-8' }
  })
}

/**
 * 处理静态文件请求
 * @param {Request} request 
 */
async function handleStatic(request) {
  const url = new URL(request.url)
  const path = url.pathname
  
  try {
    // 获取资源
    const asset = await fetch(`${ASSETS_URL}${path}`)
    
    if (asset.ok) {
      // 设置正确的MIME类型
      const contentType = getContentType(path)
      
      // 返回资源
      return new Response(asset.body, {
        headers: {
          'Content-Type': contentType,
          'Cache-Control': 'public, max-age=86400'
        }
      })
    }
  } catch (e) {
    console.error(`Error fetching static asset: ${path}`, e)
  }
  
  return new Response('资源不存在', {
    status: 404,
    headers: { 'Content-Type': 'text/plain;charset=UTF-8' }
  })
}

/**
 * 渲染页面
 * @param {string} template 
 * @param {Object} data 
 */
async function renderPage(template, data = {}) {
  // 此处应该有模板渲染逻辑
  // 简化起见，我们直接返回模板名称
  return new Response(`渲染模板: ${template}，数据: ${JSON.stringify(data)}`, {
    headers: { 'Content-Type': 'text/html;charset=UTF-8' }
  })
}

/**
 * 根据文件扩展名获取内容类型
 * @param {string} path 
 */
function getContentType(path) {
  const ext = path.split('.').pop().toLowerCase()
  
  const contentTypes = {
    'html': 'text/html',
    'css': 'text/css',
    'js': 'application/javascript',
    'json': 'application/json',
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'gif': 'image/gif',
    'svg': 'image/svg+xml',
    'ico': 'image/x-icon',
  }
  
  return contentTypes[ext] || 'text/plain'
} 