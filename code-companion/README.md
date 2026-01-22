## 技术栈

- [Vue.js](https://vuejs.org/)
- [Vite](https://vitejs.dev/)
- [TypeScript](https://www.typescriptlang.org/)
- [Vue Router](https://router.vuejs.org/)
- [Tailwind CSS](https://tailwindcss.com/)
- [shadcn/ui](https://ui.shadcn.com/)

## 快速上手

### 环境要求

- [Node.js](https://nodejs.org/) (推荐 18 或更高版本)
- [npm](https://www.npmjs.com/)

### 安装步骤

1.  **克隆仓库:**
    ```sh
    git clone <your-repository-url>
    cd lingguang
    ```

2.  **安装依赖:**
    ```sh
    npm install
    ```

3.  **配置环境变量:**

    在项目根目录中创建一个 `.env` 文件，并添加您的后端 API 所需的环境变量。

    ```env
    # 示例：您的后端 API 地址
    VITE_API_BASE_URL=http://localhost:8000
    ```

4.  **运行开发服务器:**
    ```sh
    npm run dev
    ```

    应用程序将在 `http://localhost:5173` 上可用 (如果 5173 端口被占用，可能会使用其他端口)。

## 可用脚本

- `npm run dev`: 启动开发服务器并开启热重载。
- `npm run build`: 编译和压缩应用程序以用于生产环境。
- `npm run lint`: 使用 ESLint 检查代码库中的问题。
- `npm run preview`: 启动本地服务器以预览生产版本。
