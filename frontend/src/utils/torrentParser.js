/**
 * Torrent 标题解析工具
 * 从复杂的 PT 种子标题中提取元数据标签
 */

export function parseTorrentTitle(title) {
  if (!title) return {}

  const meta = {
    resolution: "",
    codec: "",
    source: "",
    audio: "",
    season: "",
    episode: "",
    hdr: [],
    group: ""
  }

  const upperTitle = title.toUpperCase().replace(/[\.\_\s]+/g, " ")

  // 1. 分辨率
  if (upperTitle.includes("2160P") || upperTitle.includes("4K")) meta.resolution = "4K"
  else if (upperTitle.includes("1080P")) meta.resolution = "1080p"
  else if (upperTitle.includes("720P")) meta.resolution = "720p"

  // 2. 视频编码
  if (upperTitle.includes("X265") || upperTitle.includes("H265") || upperTitle.includes("HEVC")) meta.codec = "H.265"
  else if (upperTitle.includes("X264") || upperTitle.includes("H264") || upperTitle.includes("AVC")) meta.codec = "H.264"

  // 3. 来源
  if (upperTitle.includes("BLURAY") || upperTitle.includes("BDMV")) meta.source = "BluRay"
  else if (upperTitle.includes("WEB DL") || upperTitle.includes("WEBDL") || upperTitle.includes("WEB RIP")) meta.source = "WEB-DL"
  else if (upperTitle.includes("HDTV")) meta.source = "HDTV"
  else if (upperTitle.includes("REMUX")) meta.source = "Remux"

  // 4. HDR / DV
  if (upperTitle.includes("HDR10")) meta.hdr.push("HDR10")
  else if (upperTitle.includes("HDR")) meta.hdr.push("HDR")
  if (upperTitle.includes(" DV ") || upperTitle.includes("DOLBY VISION") || upperTitle.includes(" Dovi ")) meta.hdr.push("DV")

  // 5. 季集情况
  const sMatch = title.match(/S(\d{1,2})/i)
  if (sMatch) meta.season = `S${sMatch[1]}`
  
  const eMatch = title.match(/E(\d{1,3})/i)
  if (eMatch) meta.episode = `E${eMatch[1]}`

  // 6. 发布组 (通常在末尾 -GROUP)
  const groupMatch = title.match(/-([a-zA-Z0-9]+)$/)
  if (groupMatch) meta.group = groupMatch[1]

  return meta
}

/**
 * 根据标签类型返回 Element Plus 预设颜色
 */
export function getTagColor(type, value) {
  if (!value) return "info"
  
  const colorMap = {
    resolution: {
      "4K": "danger",
      "1080p": "primary",
      "720p": "success"
    },
    codec: {
      "H.265": "warning",
      "H.264": "info"
    },
    source: {
      "BluRay": "primary",
      "Remux": "danger",
      "WEB-DL": "success"
    },
    hdr: "warning"
  }

  if (type === "hdr") return colorMap.hdr
  return colorMap[type]?.[value] || "info"
}
