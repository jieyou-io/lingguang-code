/**
 * Markdown 渲染工具
 * 使用 markdown-it 和 highlight.js
 */
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';

/**
 * 创建 markdown 渲染器实例
 */
export function createMarkdownRenderer() {
  const md = new MarkdownIt({
    html: false, // 禁用 HTML 标签
    linkify: true, // 自动识别链接
    typographer: true, // 启用排版优化
    breaks: true, // 转换换行符为 <br>
    highlight: (str: string, lang: string) => {
      // 代码高亮
      if (lang && hljs.getLanguage(lang)) {
        try {
          return hljs.highlight(str, { language: lang }).value;
        } catch (err) {
          console.error('Highlight error:', err);
        }
      }
      // 无语言或高亮失败，返回转义的代码
      return md.utils.escapeHtml(str);
    }
  });

  return md;
}

/**
 * 渲染 markdown 文本为 HTML
 */
export function renderMarkdown(content: string): string {
  const md = createMarkdownRenderer();
  return md.render(content);
}
