import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'

export function ChatView() {
  return (
    <div className="h-full flex flex-col">
      <MessageList />
      <ChatInput />
    </div>
  )
}

