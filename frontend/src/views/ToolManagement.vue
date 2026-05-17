<template>
  <div class="tool-management">
    <div class="header">
      <h1>工具管理</h1>
      <el-button type="primary" @click="showAddDialog = true">添加工具</el-button>
    </div>

    <el-table :data="tools" stripe>
      <el-table-column prop="name" label="名称" width="180" />
      <el-table-column prop="description" label="描述" show-overflow-tooltip />
      <el-table-column prop="implementation_type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.implementation_type === 'builtin' ? 'info' : 'success'" size="small">
            {{ row.implementation_type === 'builtin' ? '内置' : '自定义' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button size="small" @click="editTool(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="deleteTool(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showAddDialog" :title="editingTool ? '编辑工具' : '添加工具'" width="650px">
      <el-form :model="toolForm" label-width="120px">
        <el-form-item label="工具名称">
          <el-input v-model="toolForm.name" placeholder="如：web_search" :disabled="!!editingTool" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="toolForm.description" type="textarea" :rows="2" placeholder="工具功能描述（给 LLM 看）" />
        </el-form-item>
        <el-form-item label="实现类型">
          <el-select v-model="toolForm.implementation_type" style="width: 100%">
            <el-option label="内置" value="builtin" />
            <el-option label="自定义 (HTTP)" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="toolForm.implementation_type === 'custom'" label="API URL">
          <el-input v-model="customUrl" placeholder="https://api.example.com/tool" />
        </el-form-item>
        <el-form-item v-if="toolForm.implementation_type === 'custom'" label="HTTP 方法">
          <el-select v-model="customMethod" style="width: 100%">
            <el-option label="POST" value="POST" />
            <el-option label="GET" value="GET" />
          </el-select>
        </el-form-item>
        <el-form-item label="参数 Schema">
          <el-input v-model="schemaStr" type="textarea" :rows="6" placeholder='{"type": "object", "properties": {"query": {"type": "string", "description": "搜索关键词"}}}' />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="toolForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveTool" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { toolApi, type ToolDefinition } from '@/api/tools'

const tools = ref<ToolDefinition[]>([])
const showAddDialog = ref(false)
const saving = ref(false)
const editingTool = ref<ToolDefinition | null>(null)
const schemaStr = ref('{}')
const customUrl = ref('')
const customMethod = ref('POST')

const defaultForm = {
  name: '',
  description: '',
  implementation_type: 'builtin',
  is_active: true,
}

const toolForm = reactive({ ...defaultForm })

const editTool = (tool: ToolDefinition) => {
  editingTool.value = tool
  Object.assign(toolForm, {
    name: tool.name,
    description: tool.description,
    implementation_type: tool.implementation_type,
    is_active: tool.is_active,
  })
  schemaStr.value = JSON.stringify(tool.parameters_schema, null, 2)
  customUrl.value = tool.implementation_config?.url || ''
  customMethod.value = tool.implementation_config?.method || 'POST'
  showAddDialog.value = true
}

const saveTool = async () => {
  saving.value = true
  try {
    let parameters_schema = {}
    try {
      parameters_schema = JSON.parse(schemaStr.value)
    } catch {
      ElMessage.warning('参数 Schema 格式错误，请检查 JSON')
      saving.value = false
      return
    }
    const data: any = {
      ...toolForm,
      parameters_schema,
      implementation_config: toolForm.implementation_type === 'custom'
        ? { url: customUrl.value, method: customMethod.value }
        : {},
    }
    if (editingTool.value) {
      await toolApi.update(editingTool.value.id, data)
      ElMessage.success('更新成功')
    } else {
      await toolApi.create(data)
      ElMessage.success('添加成功')
    }
    showAddDialog.value = false
    editingTool.value = null
    Object.assign(toolForm, defaultForm)
    schemaStr.value = '{}'
    tools.value = (await toolApi.list() as any) || []
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const deleteTool = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定删除此工具？', '确认')
    await toolApi.delete(id)
    ElMessage.success('删除成功')
    tools.value = (await toolApi.list() as any) || []
  } catch {}
}

onMounted(async () => {
  try {
    tools.value = (await toolApi.list() as any) || []
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.tool-management {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
</style>
